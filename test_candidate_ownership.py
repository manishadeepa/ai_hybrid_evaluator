import unittest
from unittest.mock import patch
import reflex as rx
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.state import candidate_state as candidate
from ai_hybrid_evaluator.pages.candidate import results

class CandidateOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        root = rx.State(_reflex_internal_init=True)
        self.auth = await root.get_state(AuthState)
        self.state = await root.get_state(candidate.CandidateState)
        self.results = await root.get_state(results.CandidateResultsState)

    async def test_stale_or_signed_out_session_cannot_read_or_write(self):
        self.state.candidate_id = "B"
        self.state.active_assessment_id = "assessment-B"
        self.state.active_test_id = "test-B"
        for identity in ("", "A"):
            self.auth.is_candidate_authenticated = bool(identity)
            self.auth.candidate_emp_id = identity
            with patch.object(candidate, "ResponseLifecycleService") as service:
                async for _ in self.state.update_answer("forged"):
                    pass
                async for _ in self.state.confirm_submit_test():
                    pass
                await self.state.handle_time_expired()
                service.assert_not_called()
        self.auth.is_candidate_authenticated = False
        with patch.object(candidate, "ResponseLifecycleService") as service:
            await self.state.on_test_page_load()
            service.assert_not_called()

    async def test_each_candidate_cannot_start_the_others_test(self):
        assessments = [
            {"name": f"Assessment {cid}", "assigned_candidates": [cid],
             "assessment_id": f"assessment-{cid}", "test_ids": {"Test": f"test-{cid}"}}
            for cid in ("A", "B")
        ]
        self.auth.is_candidate_authenticated = True
        for identity, other in (("A", "B"), ("B", "A")):
            self.auth.candidate_emp_id = identity
            with patch.object(candidate, "AssessmentService") as catalog, patch.object(
                candidate, "ResponseLifecycleService"
            ) as service:
                catalog.return_value.load_assessments.return_value = assessments
                await self.state.start_test(f"Assessment {other}", "Test")
                service.assert_not_called()

    async def test_each_candidate_only_selects_own_result(self):
        self.auth.is_candidate_authenticated = True
        for identity, other in (("A", "B"), ("B", "A")):
            self.auth.candidate_emp_id = identity
            snapshot = {"options": {}, "assessment_id": "", "results": {},
                        "rows": [{"test_id": f"test-{identity}", "name": "Test", "is_evaluated": True}]}
            with patch.object(results, "_read_candidate_results", return_value=snapshot) as read:
                await self.results.on_load()
                read.assert_called_once_with(identity, "")
            await self.results.select_test(f"test-{other}")
            self.assertEqual(self.results.selected_test_id, "")
            await self.results.select_test(f"test-{identity}")
            self.assertEqual(self.results.selected_test_id, f"test-{identity}")

    async def test_each_candidate_can_save_own_answer(self):
        self.auth.is_candidate_authenticated = True
        for identity in ("A", "B"):
            self.auth.candidate_emp_id = identity
            self.state._bind_candidate(identity)
            self.state.active_assessment_id = f"assessment-{identity}"
            self.state.active_test_id = f"test-{identity}"
            with patch.object(candidate, "ResponseLifecycleService") as service, patch.dict(
                candidate.PERSISTED_CANDIDATE_TEST_DATA, clear=True
            ):
                async for _ in self.state.update_answer("own answer"):
                    pass
                service.return_value.save_answer.assert_called_once_with(
                    identity, f"assessment-{identity}", f"test-{identity}",
                    self.state.current_question_number, "own answer"
                )

