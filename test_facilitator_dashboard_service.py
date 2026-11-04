import unittest
from unittest.mock import patch

from backend.services.facilitator_dashboard_service import (
    FacilitatorDashboardService,
    assessment_is_assigned_to_facilitator,
)

with patch("dotenv.load_dotenv"):
    import reflex as rx
    import ai_hybrid_evaluator.state.admin_state as admin_module
    import ai_hybrid_evaluator.state.facilitator_state as state_module
    from ai_hybrid_evaluator.state.auth_state import AuthState


class InMemoryRepository:
    def __init__(self, records):
        self.records = records

    def get_all(self):
        return list(self.records)


class InMemoryEvaluationResults:
    def __init__(self, records):
        self.records = records

    def list_results(self):
        return list(self.records)


class FacilitatorDashboardServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.assessment = {
            "assessment_id": "A1",
            "name": "HoQ",
            "assigned_candidates": ["C1", "C2", "C1"],
            "all_tests": ["Formative 1", "Formative 2", "Formative 2"],
            "test_ids": {"Formative 1": "T1", "Formative 2": "T2"},
        }
        responses = [
            {
                "candidate_id": "C1",
                "assessment_id": "A1",
                "test_id": "T1",
                "assessment_name": "HoQ",
                "test_name": "Formative 1",
                "status": "Submitted",
            },
            {
                "candidate_id": "C1",
                "assessment_id": "A1",
                "test_id": "T2",
                "assessment_name": "HoQ",
                "test_name": "Formative 2",
                "status": "Submitted",
            },
            {
                "candidate_id": "C2",
                "assessment_id": "A1",
                "test_id": "T2",
                "assessment_name": "HoQ",
                "test_name": "Formative 2",
                "status": "In Progress",
            },
        ]
        assignments = [
            {
                "candidate_id": "C1",
                "assessment_id": "A1",
                "test_id": "T1",
                "status": "Submitted",
            },
            {
                "candidate_id": "C1",
                "assessment_id": "A1",
                "test_id": "T2",
                "status": "Submitted",
            },
            {
                "candidate_id": "C2",
                "assessment_id": "A1",
                "test_id": "T1",
                "status": "Submitted",
            },
            {
                "candidate_id": "C2",
                "assessment_id": "A1",
                "test_id": "T2",
                "status": "In Progress",
            },
        ]
        evaluations = [
            {
                "candidate_id": "C1",
                "assessment_id": "A1",
                "test_id": "T1",
                "assessment_name": "HoQ",
                "test_name": "Formative 1",
                "evaluation_type": "manual",
                "evaluation_status": "completed",
                "evaluated_by": "F001",
            },
            {
                "candidate_id": "C1",
                "assessment_id": "A1",
                "test_id": "T1",
                "assessment_name": "HoQ",
                "test_name": "Formative 1",
                "evaluation_type": "ai",
                "evaluation_status": "completed",
            },
            {
                "candidate_id": "C2",
                "assessment_id": "A1",
                "test_id": "T1",
                "assessment_name": "HoQ",
                "test_name": "Formative 1",
                "evaluation_type": "ai",
                "evaluation_status": "completed",
            },
            {
                "candidate_id": "C1",
                "assessment_id": "A1",
                "test_id": "T2",
                "assessment_name": "HoQ",
                "test_name": "Formative 2",
                "evaluation_type": "ai",
                "evaluation_status": "running",
            },
        ]
        self.service = FacilitatorDashboardService(
            evaluation_results=InMemoryEvaluationResults(evaluations),
            response_repository=InMemoryRepository(responses),
            assignment_repository=InMemoryRepository(assignments),
            legacy_response_loader=lambda *_: {},
        )

    def test_counts_submitted_and_unsubmitted_tests_and_unique_evaluations(self):
        overview = self.service.get_assessments_overview([self.assessment])[0]

        self.assertEqual(overview["total_candidate_tests"], 4)
        self.assertEqual(overview["candidate_tests_completed"], 3)
        self.assertEqual(overview["not_completed"], 1)
        self.assertEqual(overview["evaluations_completed"], 2)
        self.assertEqual(overview["pending_evaluations"], 1)
        stats = {row["test_name"]: row for row in overview["test_stats"]}
        self.assertEqual(stats["Formative 1"]["completed"], 2)
        self.assertEqual(stats["Formative 1"]["eval_completed"], 2)
        self.assertEqual(stats["Formative 1"]["evaluators"], ["F001"])
        self.assertEqual(stats["Formative 2"]["completed"], 1)
        self.assertEqual(stats["Formative 2"]["pending_eval"], 1)
        self.assertEqual(stats["Formative 2"]["not_completed"], 1)

    def test_legacy_response_fallback_is_assessment_and_test_scoped(self):
        loader = unittest.mock.Mock(return_value={"responses": [{"q_no": "Q1"}]})
        service = FacilitatorDashboardService(
            evaluation_results=InMemoryEvaluationResults([]),
            response_repository=InMemoryRepository([]),
            assignment_repository=InMemoryRepository([]),
            legacy_response_loader=loader,
        )

        overview = service.get_assessments_overview([self.assessment])[0]

        self.assertEqual(overview["candidate_tests_completed"], 4)
        self.assertEqual(loader.call_count, 4)
        loader.assert_any_call("C1", "HoQ", "Formative 1")

    def test_overview_search_is_case_insensitive_and_assessment_scoped(self):
        rows = [
            {"assessment_name": "House of Quality"},
            {"assessment_name": "QFD"},
        ]

        self.assertEqual(
            FacilitatorDashboardService.filter_overview(rows, "quality"),
            [rows[0]],
        )
        self.assertEqual(FacilitatorDashboardService.filter_overview(rows, " "), rows)

    def test_facilitator_access_supports_multi_and_legacy_assignment_fields(self):
        self.assertTrue(
            assessment_is_assigned_to_facilitator(
                {"facilitator_ids": ["F001", "F002"]}, "F002"
            )
        )
        self.assertFalse(
            assessment_is_assigned_to_facilitator(
                {"facilitator_ids": ["F001", "F002"]}, "F003"
            )
        )
        self.assertTrue(
            assessment_is_assigned_to_facilitator(
                {"facilitator_id": "F001"}, "F001"
            )
        )
        self.assertFalse(assessment_is_assigned_to_facilitator({}, ""))

    def test_any_dashboard_selector_updates_all_sections(self):
        root = rx.State(_reflex_internal_init=True)
        state = root.get_substate(
            tuple(state_module.FacilitatorState.get_full_name().split("."))
        )

        state.set_dashboard_evaluation_assessment_name("HoQ")

        self.assertEqual(state.dashboard_completion_assessment_name, "HoQ")
        self.assertEqual(state.dashboard_evaluation_assessment_name, "HoQ")
        self.assertEqual(state.dashboard_collaboration_assessment_name, "HoQ")

    async def test_signed_in_facilitator_sees_only_assigned_assessments(self):
        root = rx.State(_reflex_internal_init=True)
        facilitator = root.get_substate(
            tuple(state_module.FacilitatorState.get_full_name().split("."))
        )
        admin = root.get_substate(
            tuple(admin_module.AdminState.get_full_name().split("."))
        )
        auth = root.get_substate(tuple(AuthState.get_full_name().split(".")))
        auth.facilitator_emp_id = "F001"
        auth.is_facilitator_authenticated = True
        auth.facilitator_name = "Facilitator One"
        admin.facilitators = []
        admin.candidates = []
        admin.assessments = [
            {
                "name": "Assigned",
                "assessment_id": "A1",
                "facilitator_ids": ["F001"],
                "facilitator_names": ["Facilitator One"],
                "assigned_candidates": [],
                "tests": [],
                "final_test": "",
                "test_dates": {},
                "test_ids": {},
                "status": "Draft",
            },
            {
                "name": "Not assigned",
                "assessment_id": "A2",
                "facilitator_ids": ["F002"],
                "facilitator_names": ["Facilitator Two"],
                "assigned_candidates": [],
                "tests": [],
                "final_test": "",
                "test_dates": {},
                "test_ids": {},
                "status": "Draft",
            },
        ]
        facilitator.question_papers = {}
        facilitator.saved_assessment_weightages = {}
        facilitator.weightage_inputs = {}

        from types import SimpleNamespace
        catalog = SimpleNamespace(tests=SimpleNamespace(repository=InMemoryRepository([])))
        with patch.object(state_module, "AssessmentService", return_value=catalog):
            self.assertEqual([row["name"] for row in await facilitator.my_assessments], ["Assigned"])


if __name__ == "__main__":
    unittest.main()
