"""Candidate Results: persisted lifecycle, canonical isolation, and no grading/writes."""
import unittest
from unittest.mock import patch
import test_evaluation_result_management as fixtures
with patch('dotenv.load_dotenv'):
    import reflex as rx
    import ai_hybrid_evaluator.pages.candidate.results as page
    from ai_hybrid_evaluator.state.auth_state import AuthState


class CandidateResultsLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.f=fixtures.EvaluationResultTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        # Persist assessment membership without inventing assignment/attempt status for legacy grades.
        repo=self.f.service.assessments.repository
        for a in repo.get_all():
            a['assigned_candidates']=['C1','C2'];repo.save(a)
        change=patch.object(page,'EvaluationResultService',return_value=self.f.service)
        change.start();self.addCleanup(change.stop)
        root=rx.State(_reflex_internal_init=True)
        self.auth=root.get_substate(tuple(AuthState.get_full_name().split('.')))
        self.auth.is_candidate_authenticated=True;self.auth.candidate_emp_id='C1'
        self.state=root.get_substate(tuple(page.CandidateResultsState.get_full_name().split('.')))

    def submitted(self):
        self.f.response('Submitted')
        rec=self.f.service.response_repository.get(*self.f.key)
        rec['submitted_at']='2026-09-30T10:00:00+00:00'
        self.f.service.response_repository.save(rec)

    async def row(self):
        await self.state.on_load()
        return (await self.state.tests_table_rows)[0]

    async def test_not_submitted(self):
        row=await self.row()
        self.assertEqual((row['status'],row['score'],row['submitted_on']),('Not Submitted','—','—'))

    async def test_submitted_without_candidate_state_cache(self):
        self.submitted()
        row=await self.row()
        self.assertEqual((row['status'],row['score']),('Submitted','—'))
        self.assertEqual(row['submitted_on'],'2026-09-30T10:00:00+00:00')
        self.assertEqual(row['evaluated_on'],'—')

    async def test_in_progress_and_disqualified_withhold_marks(self):
        self.f.manual_result()
        for status in ('In Progress','Disqualified'):
            self.f.response(status)
            row=await self.row()
            self.assertEqual((row['status'],row['score']),(status,'—'))
            self.assertFalse(row['is_evaluated'])

    async def test_pending_transition_is_read_only_and_unscored(self):
        self.f.response('Submitted',pending=True)
        self.f.manual_result()
        before=self.f.service.response_repository.file_path.read_bytes()
        row=await self.row()
        self.assertEqual((row['status'],row['score']),('Submission Pending','—'))
        self.assertEqual(before,self.f.service.response_repository.file_path.read_bytes())

    async def test_manual_score_and_both_timestamps(self):
        self.submitted();stored=self.f.manual_result()
        row=await self.row()
        self.assertEqual((row['status'],row['score']),('Evaluated','3 / 6'))
        self.assertEqual(row['evaluated_on'],stored['evaluated_at'])
        await self.state.select_test(row['test_id'])
        self.assertEqual(await self.state.test_submitted_on_display,'2026-09-30T10:00:00+00:00')
        self.assertEqual((await self.state.selected_test_eval_data)['candidate_id'],'C1')

    async def test_ai_finalized_score(self):
        self.submitted();run=self.f.ai_result()
        row=await self.row()
        self.assertEqual((row['status'],row['score']),('Evaluated','1 / 4'))
        self.assertEqual(row['evaluated_on'],run['updated_at'])

    async def test_manual_precedence_is_service_precedence(self):
        self.submitted();self.f.ai_result();self.f.manual_result()
        row=await self.row()
        await self.state.select_test(row['test_id'])
        data=await self.state.selected_test_eval_data
        self.assertEqual(data,self.f.service.get_result(*self.f.key))
        self.assertEqual(data['evaluation_type'],'manual')

    async def test_unfinished_and_superseded_ai_have_no_score(self):
        self.submitted();run=self.f.ai_result()
        self.f.runs.restart(run['run_id'])
        row=await self.row()
        self.assertEqual((row['status'],row['score']),('Submitted','—'))

    async def test_same_name_candidate_cannot_see_other_result(self):
        for cid in ('C1','C2'):self.f.candidates.update_candidate(cid,dict(name='Same Name'))
        self.f.manual_result('C2')
        row=await self.row()
        self.assertEqual(row['score'],'—')
        self.auth.candidate_emp_id='C2'
        self.assertEqual(await self.state.tests_table_rows,[])
        self.assertEqual((await self.row())['score'],'3 / 6')
        self.auth.candidate_emp_id='C1'
        self.assertEqual(await self.state.tests_table_rows,[])
        self.assertEqual(await self.state.selected_test_eval_data,{})

    async def test_dropdown_and_identical_test_names_remain_isolated(self):
        self.f.manual_result(assessment='A')
        row=await self.row()
        await self.state.select_test(row['test_id'])
        await self.state.set_selected_assessment('B')
        rows=await self.state.tests_table_rows
        self.assertEqual(rows[0]['test_id'],self.f.b['test_ids']['Formative 1'])
        self.assertEqual(rows[0]['score'],'—')
        await self.state.select_test(self.f.key[2])
        self.assertEqual(await self.state.selected_test_eval_data,{})
        await self.state.set_selected_assessment('A')
        self.assertEqual((await self.state.tests_table_rows)[0]['score'],'3 / 6')

    async def test_read_only_no_grading_or_result_writes(self):
        self.submitted();self.f.manual_result()
        before={p.name:p.read_bytes() for p in self.f.root.iterdir() if p.is_file()}
        with patch('backend.services.manual_evaluation_service.ManualEvaluationService.evaluate_and_save',side_effect=AssertionError('grading forbidden')), \
             patch.object(self.f.runs.repository,'save',side_effect=AssertionError('run writes forbidden')), \
             patch.object(self.f.manual,'save',side_effect=AssertionError('result writes forbidden')):
            row=await self.row()
            await self.state.select_test(row['test_id'])
            await self.state.selected_test_eval_data
            await self.state.set_selected_assessment('B')
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.f.root.iterdir() if p.is_file()})

    async def test_signed_out_and_revoked_membership_hide_results(self):
        self.f.manual_result();await self.row()
        self.auth.is_candidate_authenticated=False
        self.assertEqual(await self.state.tests_table_rows,[])
        await self.state.on_load()
        self.assertEqual(await self.state.assessment_options,[])
        self.auth.is_candidate_authenticated=True
        repo=self.f.service.assessments.repository
        a=repo.get_by_id(self.f.key[1]);a['assigned_candidates']=[];repo.save(a)
        await self.state.on_load()
        self.assertNotIn('A',await self.state.assessment_options)

    async def test_persisted_assignment_submission_fallback(self):
        self.f.service.assignment_repository.save(dict(candidate_id='C1', assessment_id=self.f.key[1],
            test_id=self.f.key[2], status='Submitted', submitted_at='2026-09-29T12:00:00+00:00'))
        row=await self.row()
        self.assertEqual((row['status'],row['score']),('Submitted','—'))
        self.assertEqual(row['submitted_on'],'2026-09-29T12:00:00+00:00')

    async def test_duplicate_assessment_names_use_ids(self):
        self.f.ai_result()
        repo=self.f.service.assessments.repository
        other=repo.get_by_id(self.f.b['assessment_id']);other['name']='A';repo.save(other)
        row=await self.row()
        self.assertEqual(row['score'],'1 / 4')
        options=await self.state.assessment_options
        self.assertEqual(len(options),2)
        target=next(label for label in options if self.f.b['assessment_id'] in label)
        await self.state.set_selected_assessment(target)
        row=(await self.state.tests_table_rows)[0]
        self.assertEqual(row['assessment_id'],self.f.b['assessment_id'])
        self.assertEqual(row['score'],'—')

    async def test_page_builds(self):
        self.assertIsNotNone(page.candidate_results_page())


if __name__=='__main__':unittest.main()
