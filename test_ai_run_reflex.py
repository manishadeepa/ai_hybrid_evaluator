"""Actual Reflex state + lifecycle worker checks with isolated persistence and no Azure."""
import asyncio
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.services.ai_evaluation_run_service import AIEvaluationRunService
from backend.repositories.ai_evaluation_run_repository import AIEvaluationRunRepository
from test_ai_evaluation_runs import records, result
with patch('dotenv.load_dotenv'):
    import reflex as rx
    import ai_hybrid_evaluator.state.facilitator_state as state_module


class ReflexRunTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.service=AIEvaluationRunService(AIEvaluationRunRepository(Path(self.temp.name)/'runs.json'))
        from backend.services.assessment_service import AssessmentService
        from backend.repositories.assessment_repository import AssessmentRepository
        self.assessments=AssessmentService(AssessmentRepository(Path(self.temp.name)/'assessments.json'),self.service.tests)
        assessment=self.assessments.create_assessment({'name':'Assessment'})
        test=self.service.tests.create_test(assessment['assessment_id'],{'test_name':'Test','test_type':'subjective'})
        self.ids={'assessment_id':assessment['assessment_id'],'test_id':test['test_id']}
        def provider(): return self.service
        provider.result_rows=AIEvaluationRunService.result_rows
        patch.object(state_module,'AIEvaluationRunService',provider).start()

        # Keep FacilitatorState on the same isolated assessment repository
        # used by this test.
        patch.object(
            state_module,
            'AssessmentService',
            return_value=self.assessments,
        ).start()

        patch('ai_hybrid_evaluator.services.ai_evaluation_service._load_client',return_value=(object(),'deployment')).start()
        self.addCleanup(patch.stopall)
        root=rx.State(_reflex_internal_init=True)
        from ai_hybrid_evaluator.state.auth_state import AuthState
        auth=root.get_substate(tuple(AuthState.get_full_name().split('.')))
        auth.facilitator_emp_id='F001'
        auth.is_facilitator_authenticated=True
        self.fac=root.get_substate(tuple(state_module.FacilitatorState.get_full_name().split('.')))
        self.fac.selected_assessment_name='Assessment'
        self.fac.selected_test_name='Test'
        self.fac.selected_evaluation_candidate='One (C1)'
        self.run=self.service.create_run('Assessment','Test',records(),labels={'C1':'One (C1)'},**self.ids)
        self.fac.active_ai_run_id=self.run['run_id']
        self.fac.show_eval_progress_modal=True

    async def execute(self,rid):
        async for event in state_module.FacilitatorState.execute_ai_run.fn(self.fac,rid):
            pass

    async def test_minimize_stop_resume_and_restart(self):
        entered=threading.Event();release=threading.Event();calls=[]
        def grade(client,deployment,record,*args):
            calls.append(record['question_no'])
            if len(calls)==1:
                entered.set()
                if not release.wait(5): raise RuntimeError('Test timeout')
            return result()
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_with_retry',side_effect=grade):
            task=asyncio.create_task(self.execute(self.run['run_id']))
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait,5))
                before=self.service.get_run(self.run['run_id'])
                self.fac.minimize_eval_progress_modal()
                self.assertFalse(self.fac.show_eval_progress_modal)
                self.assertEqual(self.service.get_run(self.run['run_id']),before)
                self.fac.stop_ai_evaluation()
                self.assertEqual(self.service.get_run(self.run['run_id'])['status'],'stop_requested')
            finally:
                release.set()
            await task
            self.assertEqual(self.fac.ai_run_status,'paused')
            self.assertEqual(self.fac.eval_progress_current,1)
            event=self.fac.resume_ai_evaluation()
            self.assertIsNotNone(event)
            await self.execute(self.run['run_id'])
            self.assertEqual(calls,['Q1','Q2','Q3'])
            self.assertEqual(self.fac.real_ai_score_display,'3 / 6')
            self.assertTrue(self.fac.ai_evaluation_done)
            self.fac.restart_ai_evaluation()
            new_id=self.fac.active_ai_run_id
            self.assertNotEqual(new_id,self.run['run_id'])
            self.assertEqual(self.fac.eval_progress_current,0)
            await self.execute(new_id)
            self.assertEqual(calls,['Q1','Q2','Q3','Q1','Q2','Q3'])
            self.assertTrue(state_module.FacilitatorState.execute_ai_run.is_background)

    async def test_selection_and_late_worker_cannot_overwrite_new_state(self):
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_with_retry',return_value=result()):
            await self.execute(self.run['run_id'])
        old=self.service.get_run(self.run['run_id'])
        self.fac.set_selected_evaluation_candidate('Other (C2)')
        self.assertEqual(self.fac.eval_progress_questions,[])
        self.assertEqual(self.fac.real_ai_score_display,'—')
        self.fac._apply_ai_run(old)
        self.assertEqual(self.fac.real_ai_score_display,'—')
        self.fac.set_selected_evaluation_candidate('One (C1)')
        self.assertEqual(self.fac.eval_progress_current,3)
        self.fac.restart_ai_evaluation()
        self.fac._apply_ai_run(old)
        self.assertEqual(self.fac.eval_progress_current,0)
        self.assertNotEqual(self.fac.active_ai_run_id,old['run_id'])

    async def test_fresh_run_shadows_legacy_score_until_results_arrive(self):
        self.fac.real_ai_results_per_candidate = {
            'One (C1):Test': {'score': '6 / 6', 'status': 'completed', 'evaluation_type': 'ai'}}
        self.fac._apply_ai_run(self.run)
        self.assertEqual(self.fac.real_ai_score_display, 'Incomplete')
        self.assertEqual(self.fac.eval_progress_current, 0)
        self.assertEqual(self.fac.real_ai_results_per_candidate['One (C1):Test']['score'], '6 / 6')

    async def test_restore_does_not_replace_manual_result(self):
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_with_retry',return_value=result()):
            await self.execute(self.run['run_id'])
        saved=dict(self.fac.real_ai_results_per_candidate)
        saved['C1:Assessment:Test']={**saved['C1:Assessment:Test'],'evaluation_type':'manual','score':'6 / 6'}
        self.fac.real_ai_results_per_candidate=saved
        self.fac.set_selected_evaluation_candidate('One (C1)')
        self.assertEqual(self.fac.real_ai_score_display,'6 / 6')

    async def test_real_start_prepares_workbook_and_dispatches_background(self):
        import pandas as pd
        from ai_hybrid_evaluator.state.admin_state import AdminState
        folder=Path(self.temp.name);paper=folder/'paper.xlsx';response=folder/'response.xlsx'
        row={'Question No':'Q1','Question':'Question','Marks':2,'Answer Key':'Reference',
             'CO':'CO1','LO':'LO1','Knowledge Type':'Conceptual','Domain':'Cognitive','RBT level':'Understand'}
        pd.DataFrame([row]).to_excel(paper,index=False)
        pd.DataFrame([dict(row,**{'Candidate Answer':'Answer'})]).to_excel(response,index=False)
        admin=await self.fac.get_state(AdminState)
        new=self.assessments.create_assessment({'name':'New Assessment'})
        typed=self.service.tests.create_test(new['assessment_id'],{'test_name':'Test','test_type':'subjective'})

        # Register the workbook as the validated canonical question paper
        # for this exact assessment/test before AI evaluation starts.
        from backend.services.question_paper_service import QuestionPaperService

        papers = QuestionPaperService(self.service.tests)
        canonical_paper = papers.import_upload(
            new['assessment_id'],
            typed['test_id'],
            'paper.xlsx',
            paper.read_bytes(),
        )

        paper = papers.upload_dir / canonical_paper['filename']

        admin.assessments=[{'name':'New Assessment','assessment_id':new['assessment_id'],'test_ids':{'Test':typed['test_id']},
                           'facilitator_ids':['F001'],'facilitator_names':['Ravi'],'assigned_candidates':['C1'],
                           'status':'Active','tests':['Test'],'final_test':''}]
        admin.candidates=[{'emp_id':'C1','name':'One','email':''}]
        self.fac.selected_assessment_name='New Assessment'
        self.fac.selected_assessment_id=new['assessment_id']
        self.fac.selected_test_name='Test'

        # This test starts a genuinely fresh evaluation selection.
        # Do not allow the run created by setUp() to be reused.
        self.fac.active_ai_run_id=''

        self.fac.question_papers={'New Assessment':{'Test':'paper.xlsx'}}
        self.fac.saved_assessment_weightages={'New Assessment':{}}

        with patch.object(state_module.rx,'get_upload_dir',return_value=folder), patch.object(state_module,'_find_response_file_path',return_value=response) as lookup:
            events=[event async for event in self.fac.run_ai_evaluation()]


        lookup.assert_called_once_with('One (C1)','Test','New Assessment',require_assessment_scope=True)
        prepared=self.service.get_run(self.fac.active_ai_run_id)

        self.assertEqual(prepared['assessment_id'],new['assessment_id']);self.assertEqual(prepared['test_id'],typed['test_id'])
        self.assertEqual(prepared['status'],'idle');self.assertEqual(prepared['completed_questions'],0)
        self.assertTrue(any(getattr(event,'handler',None) is not None and event.handler.is_background for event in events))
        with patch('ai_hybrid_evaluator.services.ai_evaluation_service._evaluate_with_retry',return_value=result()):
            await self.execute(prepared['run_id'])
        self.assertEqual(self.fac.real_ai_score_display,'1 / 2')

if __name__=='__main__': unittest.main()
